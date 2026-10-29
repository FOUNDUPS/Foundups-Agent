"""Bounded stdlib regression selection; no package startup, model or browser.

Compile complete production definitions with explicit collaborators. Queue files
are real temporary files; its lock is stubbed here (existing queue tests own lock
qualification). Provider and browser results are fixtures, not live receipts.
Run: python -B -m unittest discover -s modules/communication/video_comments/tests
     -p test_chat_manifest_inspection.py -v
"""
import ast
import asyncio
from contextlib import nullcontext
import dataclasses
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import random
import sys
import tempfile
import threading
import time
from types import ModuleType, SimpleNamespace
import typing
import unittest
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[4]


def definitions(name, path):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    body = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                value = node.value
                if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id == 'frozenset' and len(value.args) == 1):
                    continue
                ast.literal_eval(value.args[0])
            body.append(node)
    module = ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module
    module.__dict__.update(vars(typing))
    module.__dict__.update(
        dataclass=dataclasses.dataclass, asyncio=asyncio, Enum=Enum, wraps=wraps,
        RLock=threading.RLock, Event=threading.Event, threading=threading,
        os=os, Path=Path, time=time, json=json, math=math, random=random,
        hashlib=hashlib, datetime=datetime, timezone=timezone, uuid4=uuid4,
        logger=logging.getLogger(name), runtime_operation_lock=lambda *a, **k: nullcontext(),
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id.endswith('_AVAILABLE'):
            module.__dict__[node.id] = False
    exec(compile(ast.Module(body=body, type_ignores=[]), path, 'exec'), module.__dict__)
    return module


CONTEXT = definitions('_inspection_context', 'modules/communication/video_comments/src/reply_context.py')
GEN = definitions('_inspection_generator', 'modules/communication/video_comments/src/intelligent_reply_generator.py')
ANALYSIS = definitions('_inspection_analysis', 'modules/communication/video_comments/src/comment_content_analyzer.py')
QUEUE = definitions('_inspection_queue', 'modules/communication/livechat/src/operator_command_queue.py')
EXECUTOR = definitions('_inspection_executor', 'modules/communication/video_comments/skillz/tars_like_heart_reply/src/reply_executor.py')
PROCESSOR = definitions('_inspection_processor', 'modules/communication/video_comments/skillz/tars_like_heart_reply/src/comment_processor.py')
CHAT = definitions('_inspection_livechat', 'modules/communication/livechat/src/intelligent_livechat_reply.py')
for name in ('is_general_reply_model', 'parse_reply_review', 'build_grounded_prompt',
             'parse_comment_assessment', 'reply_text_is_publishable'):
    setattr(GEN, name, getattr(CONTEXT, name))
QUEUE.REPO_ROOT = ROOT
QUEUE.MAX_JSON_BYTES = 4 * 1024 * 1024
QUEUE._ACTIVE_LEDGERS = set()
QUEUE._ACTIVE_GUARD = threading.Lock()
QUEUE._TERMINAL = {'accepted', 'blocked', 'rejected', 'unknown', 'simulated', 'expired', 'superseded', 'failed'}
GOOD = dict(addresses_comment=True, coherent=True, grounded=True,
            no_internal_instructions=True, relevance=0.95, coherence=0.95)


class ReplyInspectionTests(unittest.TestCase):
    def test_model_roles(self):
        for model in ('ui-tars-1.5-7b', 'qwen2-vl', 'gemma-vision', 'qwen-embedding', 'unknown', None):
            with self.subTest(model=model):
                self.assertFalse(CONTEXT.is_general_reply_model(model))
        for model in ('qwen3-8b', 'gemma-3-4b-it', 'llama-3.1-instruct'):
            self.assertTrue(CONTEXT.is_general_reply_model(model))

    def test_gui_only_discovery_is_not_available_for_writing(self):
        model = object.__new__(GEN.IntelligentReplyGenerator)
        model.lm_studio_model_id = None
        GEN.requests = SimpleNamespace(get=lambda *a, **k: SimpleNamespace(
            status_code=200, json=lambda: {'data': [{'id': 'ui-tars-1.5-7b'}]}))
        model._check_lm_studio()
        self.assertFalse(model.lm_studio_available)
        self.assertIsNone(model.lm_studio_model_id)

    def test_explicit_gui_model_cannot_bypass_role_check(self):
        model = object.__new__(GEN.IntelligentReplyGenerator)
        model.lm_studio_model_id = 'ui-tars-1.5-7b'
        GEN.requests = SimpleNamespace(get=lambda *a, **k: SimpleNamespace(
            status_code=200, json=lambda: {'data': [{'id': 'ui-tars-1.5-7b'}]}))
        model._check_lm_studio()
        self.assertFalse(model.lm_studio_available)

    def test_named_entities_do_not_determine_agreement(self):
        analyzer = object.__new__(ANALYSIS.CommentContentAnalyzer)
        video = SimpleNamespace(title='Critical of Trump', stance='critical', critical_of=['MAGA'])
        for text in ('Trump is right. MAGA all the way!', 'Trump is wrong.', 'Did Trump say that?'):
            with self.subTest(text=text):
                self.assertIsNone(analyzer.determine_alignment(video, None, text)[0])

    def test_reviewer_requires_actual_well_typed_judgment(self):
        self.assertTrue(CONTEXT.parse_reply_review(json.dumps(GOOD))['approved'])
        bad = [None, '', 'gibberish', '[]', '{}', json.dumps({**GOOD, 'relevance': True}),
               json.dumps({**GOOD, 'coherence': 0.79}), json.dumps({**GOOD, 'grounded': False}),
               json.dumps({**GOOD, 'coherence': float('nan')})]
        for raw in bad:
            with self.subTest(raw=raw):
                self.assertFalse(CONTEXT.parse_reply_review(raw)['approved'])

    def test_theme_enters_prompt_with_comment_and_private_instructions(self):
        result = CONTEXT.build_grounded_prompt('Where is the hornet film?', 'Aki', None, 1,
            'Hornet documentary', '', '', None, theme_context={'message': 'HornetHunter.com'})
        self.assertIn('Where is the hornet film?', result)
        self.assertIn('HornetHunter.com', result)
        self.assertIn('Answer the actual comment first', result)
        self.assertIn('Do not announce receipt', result)

    def test_signature_does_not_append_theme(self):
        model = object.__new__(GEN.IntelligentReplyGenerator)
        model._current_reply_theme = {'message': 'PRIVATE THEME MUST NOT BE APPENDED'}
        result = model._add_0102_signature('The film is on the website.', tier=1)
        self.assertNotIn('PRIVATE THEME', result)

    def test_inspector_sends_original_comment_and_rejects_bad_reply(self):
        calls = []
        def post(*args, **kwargs):
            calls.append(kwargs['json'])
            return SimpleNamespace(status_code=200, json=lambda: {'choices': [
                {'message': {'content': json.dumps({**GOOD, 'coherent': False})}}]})
        model = object.__new__(GEN.IntelligentReplyGenerator)
        model._generation_lock = threading.RLock()
        model.lm_studio_available, model.lm_studio_model_id = True, 'qwen3-8b'
        model.qwen_engine = None
        GEN.requests = SimpleNamespace(post=post)
        result = model.inspect_reply({'text': 'Where is the film?'}, 'asdf zzzz 0102')
        self.assertFalse(result['approved'])
        self.assertIn('Where is the film?', calls[0]['messages'][1]['content'])
        self.assertEqual(calls[0]['temperature'], 0)

    def test_click_success_without_readback_remains_unknown(self):
        from modules.communication.video_comments.src.commenter_history_store import CommenterHistoryStore
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        executor = object.__new__(EXECUTOR.BrowserReplyExecutor)
        executor.history_store = CommenterHistoryStore(Path(directory.name) / 'history.db')
        executor.driver = SimpleNamespace(execute_script=lambda *a: None)
        executor._bind_reply_target = lambda *a: True
        executor._reply_snapshot = lambda *a: dict(complete=True, ids=[], matching_ids=[])
        async def submit(*a, **k):
            executor._submit_invoked = True
            return True
        executor._execute_reply_unverified = submit
        async def no_wait(*a):
            return None
        with patch.object(EXECUTOR.asyncio, 'sleep', no_wait):
            self.assertFalse(asyncio.run(executor.execute_reply(1, 'draft', expected_comment={
                'text':'c', 'author_name':'Aki', 'comment_id':'original', 'video_id':'video',
                '_target_channel_id':'receiving'})))
        self.assertEqual(executor.last_submission_status, 'unknown')

    def test_new_owner_readback_is_required(self):
        from modules.communication.video_comments.src.commenter_history_store import CommenterHistoryStore
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        executor = object.__new__(EXECUTOR.BrowserReplyExecutor)
        executor.history_store = CommenterHistoryStore(Path(directory.name) / 'history.db')
        executor.driver = SimpleNamespace(execute_script=lambda *a: None)
        executor._bind_reply_target = lambda *a: True
        snapshots = iter([dict(complete=True, ids=[], matching_ids=[]),
                          dict(complete=True, ids=['new'], matching_ids=['new'])])
        executor._reply_snapshot = lambda *a: next(snapshots)
        async def submit(*a, **k):
            executor._submit_invoked = True
            return True
        executor._execute_reply_unverified = submit
        self.assertTrue(asyncio.run(executor.execute_reply(1, 'draft', expected_comment={
            'text':'c', 'author_name':'Aki', 'comment_id':'original', 'video_id':'video',
            '_target_channel_id':'receiving'})))
        self.assertEqual(executor.last_submission_status, 'verified')

    def test_nested_submission_cannot_bypass_inspection(self):
        executor = object.__new__(EXECUTOR.BrowserReplyExecutor)
        self.assertFalse(asyncio.run(executor.execute_nested_reply(1, 0, 'unreviewed')))

    def test_rejected_draft_never_reaches_posting(self):
        processor = object.__new__(PROCESSOR.CommentProcessor)
        processor.target_channel_id = 'receiving-channel'
        processor.extract_comment_data = lambda _: dict(text='Where is the film?', author_name='Aki')
        processor._get_context_flags = lambda _: {}
        processor.human = None
        processor.check_moderators = processor.use_vision = processor.action_debug = False
        processor.reply_basic_only = processor.reply_debug_tags = False
        processor.no_classification = True
        processor._randomize_action_queue = lambda actions: actions
        processor._get_random_delay_multiplier = lambda: 0
        processor.delay_multiplier = 0
        processor.stats = {'replies': 0}
        async def generate(*a):
            return 'gibberish 0102', 'qwen'
        async def reject(*a):
            return {'approved': False, 'reason': 'review_rejected'}
        processor._await_reply_generation = generate
        processor._inspect_reply = reject
        posted = []
        async def post(*a, **k):
            posted.append(a)
            return True
        processor.reply_executor = SimpleNamespace(execute_reply=post)
        PROCESSOR.INTELLIGENT_REPLIES_AVAILABLE = True
        with patch.dict(os.environ, {'YT_ALLOW_GENERIC_REPLY_FALLBACK': 'false'}):
            result = asyncio.run(processor.engage_comment(1, do_like=False, do_heart=False))
        self.assertFalse(result['reply'])
        self.assertEqual(posted, [])
        self.assertIn('review_rejected', result['errors'])

    def test_changed_theme_blocks_a_stale_draft(self):
        generator = object.__new__(GEN.IntelligentReplyGenerator)
        generator._load_reply_theme = lambda: {'source_command_id': 'newer'}
        review = generator.inspect_reply({'text': 'Question', '_reply_theme': {
            'source_command_id': 'old'}}, 'A draft')
        self.assertFalse(review['approved'])
        self.assertEqual(review['reason'], 'theme_changed_or_expired')

    def test_livechat_theme_changes_prompt_instead_of_emitting_a_receipt(self):
        calls = []
        chat = object.__new__(CHAT.IntelligentLivechatReply)
        chat.classify_chatter = lambda *a: SimpleNamespace()
        chat.grok_available = True
        chat.system_prompt = 'Reply concisely'
        def respond(**kwargs):
            calls.append(kwargs)
            return (json.dumps(GOOD) if len(calls) == 2 else
                    'The documentary details are on HornetHunter.com.')
        chat.grok_client = SimpleNamespace(get_response=respond)
        theme = {'message': 'New Hornet Hunter website', 'source_command_id': 'voice-1'}
        news_module = SimpleNamespace(get_news_context=lambda message: None)
        queue_module = SimpleNamespace(load_active_theme=lambda surface: theme)
        with patch.dict(sys.modules, {
            'modules.communication.livechat.src.operator_command_queue': queue_module,
            'modules.communication.video_comments.src.reply_context': CONTEXT,
            'modules.communication.livechat.src.news_context_provider': news_module}), patch.object(CHAT.random, 'random', lambda: 1):
            reply = chat.generate_reply('Where can the film details be found?', 'Aki', 'viewer')
        self.assertIn('HornetHunter.com', reply)
        self.assertNotIn('activated', reply)
        self.assertIn('Where can the film details be found?', calls[0]['prompt'])
        self.assertIn('New Hornet Hunter website', calls[0]['prompt'])
        self.assertIn('Do not copy it verbatim', calls[0]['prompt'])

    def test_context_activation_is_private_and_replay_is_inert(self):
        with tempfile.TemporaryDirectory() as folder:
            root, sent = Path(folder), []
            async def send(message, **kwargs):
                sent.append(message)
                return True
            gates = dict(stop_active=False, yt_automation=True, livechat_send=True,
                         announcements=True, comment_engagement=True, livechat_dry_run=False)
            QUEUE.gate_snapshot = lambda: gates
            queue = QUEUE.OperatorCommandQueue(SimpleNamespace(livechat=SimpleNamespace(send_chat_message=send)),
                command_path=root/'inbox.json', acknowledgement_path=root/'ack.json',
                state_path=root/'state.json', poll_interval_seconds=0)
            command = {'id': 'voice-theme-1', 'action': 'set_context', 'payload': {
                'message': 'HornetHunter.com documentary', 'surfaces': ['livechat', 'comments']}}
            queue.command_path.write_text(json.dumps({'version': 1, 'commands': [command]}))
            first = asyncio.run(queue.poll_once())
            self.assertTrue(first['results'][0]['result']['context_activated'])
            self.assertEqual(sent, [])
            self.assertEqual(json.loads(queue.state_path.read_text())['active_context']['source_command_id'], 'voice-theme-1')
            self.assertEqual(asyncio.run(queue.poll_once())['processed'], 0)
            self.assertEqual(sent, [])
            queue.command_path.write_text(json.dumps({'version': 1, 'commands': [
                {'id': 'explicit-public-1', 'action': 'announce', 'payload': {'message': 'Public update'}}]}))
            asyncio.run(queue.poll_once())
            self.assertEqual(sent, ['Public update'])


if __name__ == '__main__':
    unittest.main()
